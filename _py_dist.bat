rd /q /s .\cpkt\rpc\ice
xcopy .\other_git\rpc_ice\py .\cpkt\rpc\ice /I /S
copy nul .\cpkt\rpc\ice\__init__.py> nul

del /q /f .\dist\*

set ifile=setup_.py
set ofile=setup.py

del /q /f %ofile%

set version=%date:~2,2%.%date:~5,2%%date:~8,2%.%time:~0,2%%time:~3,2%

.\bin\sed.exe   's/_x_version_x_/%version%/g'   %ifile%  > %ofile%

py -3 ice2init.py

py -3 setup.py sdist

pause