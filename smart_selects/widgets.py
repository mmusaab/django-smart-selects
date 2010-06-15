from django.conf import settings
from django.forms.widgets import Select
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.db.models import get_model
import locale
from smart_selects.utils import unicode_sorter

JQUERY_URL = getattr(settings, 'JQUERY_URL', 'http://ajax.googleapis.com/ajax/libs/jquery/1.3.2/jquery.min.js')
        
class ChainedSelect(Select):
    def __init__(self, app_name, model_name, chain_field, model_field, show_all, *args, **kwargs):
        self.app_name = app_name
        self.model_name = model_name
        self.chain_field = chain_field
        self.model_field = model_field
        self.show_all = show_all
        super(Select, self).__init__(*args, **kwargs)
        
    class Media:
        js = (
            JQUERY_URL,
        )
    
    def render(self, name, value, attrs=None, choices=()):
        if len(name.split('-')) > 1: # formset
            chain_field = '-'.join(name.split('-')[:-1] + [self.chain_field])
        else:
            chain_field = self.chain_field 
        
        if self.show_all:
            url = "/".join(reverse("chained_filter_all", kwargs={'app':self.app_name,'model':self.model_name,'field':self.model_field,'value':"1"}).split("/")[:-2])
        else:
            url = "/".join(reverse("chained_filter", kwargs={'app':self.app_name,'model':self.model_name,'field':self.model_field,'value':"1"}).split("/")[:-2])
        js = """
        <script type="text/javascript">
        $(document).ready(function(){
            function fill_field(val, init_value){
                if (!val || val==''){
                    options = '<option value="">---------</option>';
                    $("#%(id)s").html(options);
                    $('#%(id)s option:first').attr('selected', 'selected');
                    return;
                }
                $.getJSON("%(url)s/"+val+"/", function(j){
                    var options = '';
                    if(j.length > 1 || j.length == 0){
                        options += '<option value="">---------</option>';
                    }
                    for (var i = 0; i < j.length; i++) {
                        options += '<option value="' + j[i].value + '">' + j[i].display + '</option>';
                    }
                    $("#%(id)s").html(options);
                    if(init_value){
                        $('#%(id)s option[value="'+ init_value +'"]').attr('selected', 'selected');
                    }else{
                        $('#%(id)s option:first').attr('selected', 'selected');
                    }
                    $("#%(id)s").trigger('change');
                })
            }
            
            var start_value = $("select#id_%(chainfield)s")[0].value
            fill_field(start_value, "%(value)s");
            
            
            $("select#id_%(chainfield)s").change(function(){
                var val = $(this).val();
                fill_field(val);
                
            })
        })
        </script>
        
        """ % {"chainfield":chain_field, "url":url, "id":attrs['id'], 'value':value, 'all':all}
        final_choices=[]
        
        if value:
            item = self.queryset.filter(pk=value)[0]
            try:
                pk = getattr(item, self.model_field+"_id")
                filter={self.model_field:pk}
            except AttributeError:
                try: # maybe m2m?
                    pks = getattr(item, self.model_field).all().values_list('pk', flat=True)
                    filter={self.model_field+"__in":pks}
                except AttributeError:
                    try: # maybe a set?
                        pks = getattr(item, self.model_field+"_set").all().values_list('pk', flat=True)
                        filter={self.model_field+"__in":pks}
                    except: # give up
                        filter = {}
            filtered = list(get_model( self.app_name, self.model_name).objects.filter(**filter).distinct())
            filtered.sort(cmp=locale.strcoll, key=lambda x:unicode_sorter(unicode(x)))
            for choice in filtered:
                final_choices.append((choice.pk, unicode(choice)))
        if len(final_choices)>1:
            final_choices = [("", ("---------"))] + final_choices
        if self.show_all:
            final_choices.append(("", ("---------")))
            self.choices = list(self.choices)
            self.choices.sort(cmp=locale.strcoll, key=lambda x:unicode_sorter(x[1]))
            for ch in self.choices:
                if not ch in final_choices:
                    final_choices.append(ch)
        self.choices = ()
        output = super(ChainedSelect, self).render(name, value, attrs, choices=final_choices)
        output += js
        return mark_safe(output)
