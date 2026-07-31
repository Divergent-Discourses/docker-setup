FROM nginx:latest

# Install dos2unix
RUN apt-get update && apt-get install -y dos2unix

COPY public /home/vmuser/public/
COPY miniconda3 /home/vmuser/miniconda3/
COPY nginx/default /etc/nginx/sites-available/default
COPY data /mnt/data/
# Change sites-available to conf.d/default.conf
COPY nginx/default /etc/nginx/conf.d/default.conf

# Fix line endings for all scripts
RUN find /home/vmuser/miniconda3/envs/corpus_ui/bin/ -type f | xargs dos2unix 2>/dev/null || true
RUN find /home/vmuser/public -type f \( -name "*.py" -o -name "*.sh" \) | xargs dos2unix 2>/dev/null || true

EXPOSE 80
EXPOSE 443

