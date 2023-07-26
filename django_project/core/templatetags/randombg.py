import random
from django import template

register = template.Library()


@register.simple_tag
def randombg():
    rand = random.randint(0, 12)
    filePrefix = 'Brand_Template_PPT_Presentation.pptx'
    return filePrefix + ('_' + str(rand) if rand > 0 else '') + '.jpg'
