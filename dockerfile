FROM nginx:latest

COPY public /home/vmuser/public/
COPY miniconda3 /home/vmuser/miniconda3/
COPY nginx/default /etc/nginx/sites-available/default
COPY data /mnt/data/

# Change sites-available to conf.d/default.conf
COPY nginx/default /etc/nginx/conf.d/default.conf

EXPOSE 80
EXPOSE 443

