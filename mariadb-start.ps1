# Run 'sc.exe start MariaDB' with elevated privileges
Start-Process sc.exe -ArgumentList "start MariaDB" -Verb RunAs
