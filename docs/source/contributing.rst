Contributing
============


Contributions are what make the open source community such an amazing place to be learn, inspire, and create.
Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (``git checkout -b feature/AmazingFeature``)
3. Commit your Changes (``git commit -m 'Add some AmazingFeature'``)
4. Push to the Branch (``git push origin feature/AmazingFeature``)
5. Open a Pull Request

To tests on your changes locally, run:

.. code-block:: bash

   $ pip install -r test_requirements.txt
   $ tox .

This will run your changes on python-2 and python-3

Documentation for any new changes to APIs are a must. We use `Sphinx <https://www.sphinx-doc.org/en/master/>`__ and to
build the documentation locally, run:

.. code-block:: bash

   $ cd docs/
   $ make html
       # or on windows
   $ make.bat html
