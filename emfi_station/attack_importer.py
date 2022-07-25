# EMFI Station - Orchestrate electromagnetic fault injection attacks
# Copyright (C) 2022 Niclas Kühnapfel
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import importlib.util
from inspect import isclass

from .attack import Attack


class AttackImporter:
    """
    Imports attack scripts from given folder.
    """
    def __init__(self, path: str = None) -> None:
        """
        Loads attack classes and checks for duplicates.
        :param path: Path to attacks folder
        """
        self.attack_cls = []
        if path is not None:
            self.__load_attacks(path)
            self.__check_names()

    def __load_attacks(self, path: str) -> None:
        """
        Loads attacks into a list.
        :param path: Path to attacks folder.
        :return: None
        """
        path = os.path.abspath(path)
        for src_file in [f[:-3] for f in os.listdir(path) if f.endswith('.py') and f != '__init__.py']:
            spec = importlib.util.spec_from_file_location(src_file, path + '/' + src_file + '.py')
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attribute_name in dir(mod):
                attribute = getattr(mod, attribute_name)
                if isclass(attribute) and issubclass(attribute, Attack) and Attack != attribute:
                    self.attack_cls.append(attribute)

    def get_attack_names(self) -> list[str]:
        """
        Returns all currently loaded attack names.
        :return: List of attack names.
        """
        return [a.name() for a in self.attack_cls]

    def get_attack_by_name(self, name: str) -> object or None:
        """
        Returns attack object by its name.
        :param name: Name of the attack.
        :return: Attack object if found, None if not found.
        """
        for a in self.attack_cls:
            if a.name() == name:
                return a
        return None

    def __check_names(self) -> None:
        """
        Check attack names for duplicates and raises an exception
        if duplicates are found. Each attack should have its own name.
        :return: None
        """
        names = []
        for a in self.attack_cls:
            name = a.name()
            if name in names:
                raise Exception
            else:
                names.append(name)
