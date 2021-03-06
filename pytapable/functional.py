import inspect

from functools import partial, wraps
from .hooks import BaseHook, Tap, HookConfig
from .utils import merge_args_to_kwargs, get_arg_spec_py2_py3


class FunctionalTap(Tap):
    def __init__(self, name, fn, before, after):
        """
        Functional taps is used in combination with a :class:`FunctionalBaseHook`

        Args:
            name (str): Name of the tap
            fn (Callable): This will be called when the hook triggers
            before (bool): If true, this tap will be called *before* the hooked function executes
            after (bool): If true, this tap will be called *after* the hooked function executes
        """
        super(FunctionalTap, self).__init__(name, fn)
        self.before = before
        self.after = after


class FunctionalHook(BaseHook):
    """
    Functional hooks are created when :class:`CreateHook` is used to decorate a class function. When a functional
    hook is tapped, a :class:`FunctionalTap` is created. Look at :func:`FunctionalHook.call` to see how taps are
    called
    """
    HOOK_TYPE = BaseHook.FUNCTIONAL

    def tap(self, name, fn, before=True, after=True):
        """
        Creates a :class:`FunctionalTap` for this hook

        Args:
            name (str): Name of the tap
            fn (Callable): This will be called when the hook triggers
            before (bool): If true, this tap will be called *before* the hooked function executes
            after (bool): If true, this tap will be called *after* the hooked function executes
        """
        tap = FunctionalTap(
            name=name,
            fn=fn,
            before=before,
            after=after
        )
        tap = self.interceptor.register(
            context={
                'hook': self
            },
            tap=tap
        ) if self.interceptor else tap
        self.taps.append(tap)

    def call(self, fn_kwargs, is_before, fn_output=None):
        """
        Triggers all taps installed on this hook.

        Taps receive predefined arguments `(context, fn_args, fn_output)`

        .. code-block:: python

           # Arguments to a callback

           fn_kwargs: **kwargs

           fn_output = Optional[Any]

           context = {
             'hook': FunctionalHook,
             'tap': FunctionalTap,
             'is_before': is_before
           }

        Args:
            fn_kwargs (dict): The kwargs the hooked function was called with. \*args should be converted to \*\*kwargs.
                See `utils.merge_args_to_kwargs`
            is_before (bool): True if the hook is being called after the hooked function has executed
            fn_output (Optional[Any]): The return value of the hooked function if any. None otherwise
        """
        for tap in self.taps:
            if (tap.before and is_before) or (tap.after and not is_before):
                tap.fn(
                    context={
                        'hook': self,
                        'tap': tap,
                        'is_before': is_before
                    },
                    fn_output=fn_output,
                    fn_kwargs=fn_kwargs,
                )


class HookMapping(dict):
    """
    A dict like object with helper methods to inherit hooks and add hooks
    """

    def inherit_hooks(self, hookable_instance):
        """
        Given an instance which extends the :class:`HookableMixin` class, inherits all hooks from it to expose it on
        top level

        Args:
            hookable_instance (HookableMixin): Instance from which to inherit hooks
        """
        self.update(hookable_instance.hooks)

    def add_hook(self, hook):
        """
        Adds the passed in hook to the hooks mapping dict

        Args:
            hook (BaseHook): Hook to add to the mapping
        """
        self[hook.name] = hook


class HookableMixin(object):
    """
    Mixin which instantiates all the decorated class methods. This is needed for decorated class methods

    Instantiates an instance property ``self.hook`` which is a :class:`HookMapping`
    """
    def __init__(self, *args, **kwargs):
        super(HookableMixin, self).__init__(*args, **kwargs)
        self.hooks = HookMapping()
        klass = type(self)
        for method in map(partial(getattr, klass), dir(klass)):
            if hasattr(method, '_pytapable'):
                hook_config = getattr(method, '_pytapable')
                self.hooks.add_hook(FunctionalHook(
                    name=hook_config.name,
                    interceptor=hook_config.interceptor
                ))


class CreateHook(object):
    """
    Decorator used for creating Hooks on instance methods. It takes in a name and optionally an instance of a
    :class:`HookInterceptor`.

    .. note::
        This decorator doesn't actually create the hook. It just annotates the method. The hooks are created by the
        :class:`HookableMixin` upon instantiation

    .. note::
        The wrapped function may be called with different combinations of positional and named args which would make it
        difficult for the callback function owner to know whether to read values from `*args` or `**kwargs`. We
        instead convert all positional args to named args to remove any ambiguity

        See :func:`utils.merge_args_to_kwargs` for implementation details
    """
    def __init__(self, name, interceptor=None):
        self.name = name
        self.interceptor = interceptor

    def __call__(self, fn):
        merge_args_to_kwargs_for_fn = partial(merge_args_to_kwargs, get_arg_spec_py2_py3(fn))

        @wraps(fn)
        def wrapper(*args, **kwargs):
            hook = args[0].hooks[self.name]

            # Merge *args and **kwargs to just **kwargs
            fn_kwargs = merge_args_to_kwargs_for_fn(args, kwargs)

            # Before call
            hook.call(fn_kwargs=fn_kwargs, fn_output=None, is_before=True)

            # Call wrapped function
            out = fn(*args, **kwargs)

            # After call
            hook.call(fn_kwargs=fn_kwargs, fn_output=out, is_before=False)

            return out

        hook_config = HookConfig(name=self.name, interceptor=self.interceptor)
        wrapper._pytapable = hook_config
        return wrapper