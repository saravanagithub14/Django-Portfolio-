with open('contact.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('class="social-link"', 'class="contact-social-link"')
content = content.replace('.social-link', '.contact-social-link')

with open('contact.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated contact.html class names successfully.')
