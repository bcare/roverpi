import sys

import wx
import wx.html2

import pylibconfig2 as pycfg


def convert_event_string_into_object(evt_string):
    return getattr(wx,''.join(evt_string.split('.')[1:]))

class WidgetState():
    def __init__(self, widget_parent=None,**kwargs):
        ## widget_parent, bindings={}, methods_calls={}, exit_methods_calls={}, name=''

        self.widget_parent = widget_parent
        
        if 'bindings' in kwargs:
                
            ### bindings is a dictionary of the form :
            ### {'<widgetname>':[[<event>,<name of method in widget_parent>, (.. other args for Bind)],... ]} \
            self.bindings = kwargs['bindings']
            
        if 'methods_calls' in kwargs:
            
            ### methods_calls is a dictionary :
            ### {'<widgetname>':[<method name>, <method args...>],... }
            self.methods_calls = kwargs['methods_calls']


        if 'exit_methods_calls' in kwargs:
                
            ### bindings is a dictionary of the form :
            ### {'<widgetname>':[[<event>,<name of method in widget_parent>, (.. other args for Bind)],... ]} \
            self.exit_methods_calls = kwargs['exit_methods_calls']
           
            
        if 'name' in kwargs:
            self.name = kwargs['name']

    

    def set_widget_parent(self, widget_parent):
        self.widget_parent = widget_parent
        
    def commit_bindings(self,dict_bindings=None):
        if dict_bindings is None:
            dict_bindings = self.bindings
            
        for widgetname in dict_bindings.keys():
            ## use 'self' as a setting group name
            ## to act on the frame (i.e. the widget_parent)
            if widgetname == "self":
                widget_object = self.widget_parent
                
            elif hasattr(self.widget_parent, widgetname):
                widget_object = getattr(self.widget_parent, widgetname)
            else:
                ## don't do anything the widget was not found.
                break
            
            for binding in dict_bindings[widgetname]:
                event = binding[0]
                handler_name = binding[1]
                if handler_name == "None":
                    handler_name = None    

                handler = None
                
                if handler_name is not None:    
                    handler = getattr(self.widget_parent, binding[1])
                        
                bindargs = [event, handler] + binding[2:]
                widget_object.Bind(*bindargs)
            

    def commit_methods(self,dict_methods_calls=None):
        if dict_methods_calls is None:
            dict_methods_calls = self.methods_calls
            
        for widgetname in dict_methods_calls.keys():
            if widgetname == "self":
                widget_object = self.widget_parent
            elif hasattr(self.widget_parent, widgetname):
                widget_object = getattr(self.widget_parent, widgetname)
            else:
                break
            
            methods_calls = dict_methods_calls[widgetname]
            for method_call in methods_calls:
                method_name = method_call[0]
                if hasattr(widget_object, method_name):
                    method = getattr(widget_object, method_name)
                    method_args = method_call[1:]
                    method(*method_args)
                    
                

    def commit(self):
        self.commit_bindings()
        self.commit_methods()

    def uncommit_bindings(self):
        """ Take each binding of the state and create a list of 
        unbindings (i.e. same event but handler=None and no args)
        and commit them."""
        if hasattr(self, 'bindings'):
            dict_bindings = self.bindings
            dict_unbindings = {}
            for widgetname in dict_unbindings:
                bindings = dict_unbindings[widgetname]
                unbindings = []
                for binding in bindings:
                    unbindings.append(bindings[0]+[None])
                dict_unbindings[widgetname] = unbindings
            
            self.commit_bindings(dict_bindings=dict_unbindings)

    def uncommit(self):
        self.uncommit_bindings()
        if hasattr(self, 'exit_methods_calls'):
            self.commit_methods(self.exit_methods_calls)
        
        
class StatesGroup():
    def __init__(self,widget_parent,**kwargs):

        self.states = {}
        self.widget_parent = widget_parent
        
        if 'filepath' in kwargs:
            self.load_from_file(self.filepath)

        if 'fromstring' in kwargs:
            self.load_from_string(self.fromstring)


      #  print dir(self.widget_parent)
            
    def load_from_file(self,filepath):
        cfg = pycfg.Config()
        cfg.read_file(filepath)
        self.load_from_config(cfg)

    def load_from_string(self, fromstring):
        cfg = pycfg.Config()
        cfg.read_string(fromstring)
        self.load_from_config(cfg)
            
    def load_from_config(self,cfg):
        
        ### for each state (root keys):
        for statename in cfg.keys():
            dict_bindings = {}
            dict_methods_calls = {}

            statecfg = cfg.get(statename)
            
            for widgetname in statecfg.keys():

                widgetcfg = statecfg.get(widgetname)

                ### get bindings :
                if "bindings" in widgetcfg.keys():
                    bindings_group = widgetcfg.bindings
                    dict_bindings[widgetname]=[]
                    for binding in bindings_group:
                        binding_list = binding[:]
                        binding_list[0] = convert_event_string_into_object(binding_list[0])
                        dict_bindings[widgetname].append(binding_list)
                        ### convert the event object string into a wx object :
                        
                        
                ### get methods_calls :
                if "methods_calls" in widgetcfg.keys():
                    methods_calls_group = widgetcfg.methods_calls
                    dict_methods_calls[widgetname] = []
                    for method_call in methods_calls_group:
                        dict_methods_calls[widgetname].append(method_call)

            
            ### widgets loaded,create the state object:
            state_args = {"widget_parent":self.widget_parent,"bindings":dict_bindings, "methods_calls":dict_methods_calls, "name":statename}
            self.states[statename] = WidgetState(**state_args)


    def commit(self, statename):
        self.states[statename].commit()
        
    def uncommit(self, statename):
        self.states[statename].uncommit()



if __name__ == "__main__":
    sg = StatesGroup(None, filepath=sys.argv[1])
    for state in sg.states:
        print "name : ",sg.states[state].name
        print sg.states[state].bindings
        print sg.states[state].methods_calls
        
        
