# Copyright 2018 Bryan Bonvallet.
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

from .alchemy import Database

def build_driver(debug=False):
    driver = Database()
    driver.build('sqlite:///:memory:', debug=debug)
    return driver
