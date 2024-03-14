import tkinter as tk
import os
from tkinter import filedialog, messagebox
from dtrack_params import dtrack_params

import json


class ProjectFrame(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.__labelframe = tk.LabelFrame(self, text='Session info')
        self.__label = tk.Label(self.__labelframe, 
                                text='Current session')
        self.__btn_select =  tk.Button(self.__labelframe,
                                       text='Select project',
                                       command=self.__select_callback)
        self.__btn_new = tk.Button(self.__labelframe,
                                   text='New project',
                                   command=self.__new_callback)
        self.__ent_project = tk.Entry(self.__labelframe)
        
        # If the user has previously worked on a project and that project
        # still exists, populate the project entry with the relevant info.
        cached_project = dtrack_params['current_project']
        if not (cached_project == None):
            if os.path.exists(cached_project):
                self.__ent_project.insert(0, cached_project)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        n_cols = 5
        for i in range(n_cols):
            if (i == 1) or (i==2) or (i==3):
                self.__labelframe.columnconfigure(i, weight=1)
                continue
            self.__labelframe.columnconfigure(i, weight=0)

        self.__labelframe.rowconfigure(0,weight=1)

        self.__labelframe.grid(row=0, column=0,sticky='ew')
        self.__label.grid(row=0, column=0, sticky='w')
        self.__ent_project.grid(row=0, column=1, columnspan=2, sticky='ew')               
        self.__btn_select.grid(row=0, column=3, sticky='e')
        self.__btn_new.grid(row=0, column=4, sticky='e')

    def __select_callback(self):
        """
        Spawn a file dialog when project selection window is shown.
        """
        directory = filedialog.askdirectory(
            initialdir = str(os.getcwd()),
            title = "Select project directory"
        )
        if not os.path.exists(directory):
            directory = ""
            print("Error: selected directory does not exist.")

        dtrack_params["current_project"] = directory

        self.__ent_project.delete(0, tk.END)
        self.__ent_project.insert(0, dtrack_params['current_project'])

    def __new_callback(self):
        """
        Spawn a file dialog to select the parent directory.
        """
        full_path = filedialog.asksaveasfilename(
            initialdir = str(os.getcwd()),
            title = "Save as",
            filetypes=[("Dung Track 2 Project (JSON)", "*.dt2p")]
        )

        # User cancelled 
        if not (".dt2p" in full_path):
            return

        # Check that path doesn't already exist
        parent = full_path.split(".")[0]
        confirm_message =\
              "The following directory will be created\n{}\n\n".format(parent)+\
              "Do you wish to proceed?"

        confirm = messagebox.askokcancel(title="Confirm directory", 
                                         message=confirm_message,
                                         icon='question')

        
        if confirm:
            # Create parent directory
            os.mkdir(parent)
            filename = full_path.split("/")[-1]
            full_path = parent + "/" + filename

            # Create project (JSON) file

            # This could be replaced with nicer project file init when I know
            # what's actually going to go into project files...  I think this
            # could also be made nicer by using a custom file dialog.
            # Could also create all the necessary sub-directories at this point.
            with open(full_path, "w") as f:
                project = dict()
                json.dump(project, f)

        dtrack_params["current_project"] = parent

        self.__ent_project.delete(0, tk.END)
        self.__ent_project.insert(0, dtrack_params['current_project'])


    def get_session(self):
        return self.__ent_project.get()

        