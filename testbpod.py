#!/usr/bin/env python
import subprocess as SP
import os
import unittest
import copy
import numpy as N
from bpod import BPOD
from fieldoperations import FieldOperations
import util
import parallel as parallel_mod
parallel = parallel_mod.default_instance

try: 
    from mpi4py import MPI
    rank = MPI.COMM_WORLD.Get_rank()
    distributed = MPI.COMM_WORLD.Get_size() > 1
except ImportError:
    print 'Warning: without mpi4py module, only serial behavior is tested'
    distributed = False
    rank = 0

if rank==0:
    print 'To test fully, remember to do both:'
    print '    1) python testbpod.py'
    print '    2) mpiexec -n <# procs> python testbpod.py\n'
    

class TestBPOD(unittest.TestCase):
    """ Test all the BPOD class methods """
    def setUp(self):
        self.maxDiff = 1000
        if not os.path.isdir('files_modaldecomp_test'):        
            SP.call(['mkdir','files_modaldecomp_test'])
        self.mode_nums =[2, 4, 3, 6, 9, 8, 10, 11, 30]
        self.num_direct_snaps = 40
        self.num_adjoint_snaps = 45
        self.num_states = 100
        self.index_from = 2
        self.bpod = BPOD(load_field=util.load_mat_text, save_field=util.\
            save_mat_text, save_mat=util.save_mat_text, inner_product=util.\
            inner_product, verbose=False)
        self.generate_data_set()
   

    def tearDown(self):
        parallel.sync()
        if parallel.is_rank_zero():
            SP.call(['rm -rf files_modaldecomp_test/*'], shell=True)
        parallel.sync()
    
    def generate_data_set(self):
        # create data set (saved to file)
        self.direct_snap_path = 'files_modaldecomp_test/direct_snap_%03d.txt'
        self.adjoint_snap_path = 'files_modaldecomp_test/adjoint_snap_%03d.txt'

        self.direct_snap_paths=[]
        self.adjoint_snap_paths=[]
        
        if parallel.is_rank_zero():
            self.direct_snap_mat = N.mat(N.random.random((self.num_states,self.\
                num_direct_snaps)))
            self.adjoint_snap_mat = N.mat(N.random.random((self.num_states,self.\
                num_adjoint_snaps))) 
            
            for direct_snap_index in range(self.num_direct_snaps):
                util.save_mat_text(self.direct_snap_mat[:,direct_snap_index],self.\
                    direct_snap_path%direct_snap_index)
                self.direct_snap_paths.append(self.direct_snap_path%direct_snap_index)
            for adjoint_snap_index in range(self.num_adjoint_snaps):
                util.save_mat_text(self.adjoint_snap_mat[:,adjoint_snap_index],
                  self.adjoint_snap_path%adjoint_snap_index)
                self.adjoint_snap_paths.append(self.adjoint_snap_path%\
                    adjoint_snap_index)
        else:
            self.direct_snap_paths=None
            self.adjoint_snap_paths=None
            self.direct_snap_mat = None
            self.adjoint_snap_mat = None
        if parallel.is_distributed():
            self.direct_snap_paths = parallel.comm.bcast(self.\
                direct_snap_paths, root=0)
            self.adjoint_snap_paths = parallel.comm.bcast(self.\
                adjoint_snap_paths, root=0)
            self.direct_snap_mat = parallel.comm.bcast(self.direct_snap_mat, 
                root=0)
            self.adjoint_snap_mat = parallel.comm.bcast(self.adjoint_snap_mat,
                root=0)
         
        self.hankel_mat_true = self.adjoint_snap_mat.T * self.direct_snap_mat
        
        #Do the SVD on all procs.
        self.L_sing_vecs_true, self.sing_vals_true, self.R_sing_vecs_true = util.svd(
            self.hankel_mat_true)
        self.direct_mode_mat = self.direct_snap_mat * N.mat(self.R_sing_vecs_true) *\
            N.mat(N.diag(self.sing_vals_true ** -0.5))
        self.adjoint_mode_mat = self.adjoint_snap_mat * N.mat(self.L_sing_vecs_true) *\
            N.mat(N.diag(self.sing_vals_true ** -0.5))
        
        #self.bpod.direct_snap_paths=self.direct_snap_paths
        #self.bpod.adjoint_snap_paths=self.adjoint_snap_paths
        
    def test_init(self):
        """Test arguments passed to the constructor are assigned properly"""
        # Default data members for constructor test

        data_members_default = {'save_mat': util.save_mat_text, 'load_mat':
             util.load_mat_text, 'parallel': parallel_mod.default_instance,
            'verbose': False,
            'field_ops': FieldOperations(load_field=None, save_field=None,
            inner_product=None, max_fields_per_node=2, verbose=False)}
        
        # Get default data member values
        # Set verbose to false, to avoid printing warnings during tests
        self.assertEqual(util.get_data_members(BPOD(verbose=False)), \
            data_members_default)
        
        def my_load(fname): pass
        my_BPOD = BPOD(load_field=my_load, verbose=False)
        data_members_modified = copy.deepcopy(data_members_default)
        data_members_modified['field_ops'].load_field = my_load
        self.assertEqual(util.get_data_members(my_BPOD), data_members_modified)

        my_BPOD = BPOD(load_mat=my_load, verbose=False)
        data_members_modified = copy.deepcopy(data_members_default)
        data_members_modified['load_mat'] = my_load
        self.assertEqual(util.get_data_members(my_BPOD), data_members_modified)
 
        def my_save(data, fname): pass 
        my_BPOD = BPOD(save_field=my_save, verbose=False)
        data_members_modified = copy.deepcopy(data_members_default)
        data_members_modified['field_ops'].save_field = my_save
        self.assertEqual(util.get_data_members(my_BPOD), data_members_modified)
        
        my_BPOD = BPOD(save_mat=my_save, verbose=False)
        data_members_modified = copy.deepcopy(data_members_default)
        data_members_modified['save_mat'] = my_save
        self.assertEqual(util.get_data_members(my_BPOD), data_members_modified)
        
        def my_ip(f1, f2): pass
        my_BPOD = BPOD(inner_product=my_ip, verbose=False)
        data_members_modified = copy.deepcopy(data_members_default)
        data_members_modified['field_ops'].inner_product = my_ip
        self.assertEqual(util.get_data_members(my_BPOD), data_members_modified)
                                
        max_fields_per_node = 500
        my_BPOD = BPOD(max_fields_per_node=max_fields_per_node, verbose=False)
        data_members_modified = copy.deepcopy(data_members_default)
        data_members_modified['field_ops'].max_fields_per_node =\
            max_fields_per_node
        data_members_modified['field_ops'].max_fields_per_proc = \
            max_fields_per_node * parallel.get_num_nodes()/parallel.get_num_procs()
        self.assertEqual(util.get_data_members(my_BPOD), data_members_modified)
       
        
    def test_compute_decomp(self):
        """
        Test that can take snapshots, compute the Hankel and SVD matrices
        
        With previously generated random snapshots, compute the Hankel
        matrix, then take the SVD. The computed matrices are saved, then
        loaded and compared to the true matrices. 
        """
        tol = 8
        direct_snap_path = 'files_modaldecomp_test/direct_snap_%03d.txt'
        adjoint_snap_path = 'files_modaldecomp_test/adjoint_snap_%03d.txt'
        L_sing_vecs_path = 'files_modaldecomp_test/L_sing_vecs.txt'
        R_sing_vecs_path = 'files_modaldecomp_test/R_sing_vecs.txt'
        sing_vals_path = 'files_modaldecomp_test/sing_vals.txt'
        hankel_mat_path = 'files_modaldecomp_test/hankel.txt'
        
        self.bpod.compute_decomp(direct_snap_paths=self.direct_snap_paths, 
            adjoint_snap_paths=self.adjoint_snap_paths)
        
        self.bpod.save_hankel_mat(hankel_mat_path)
        self.bpod.save_decomp(L_sing_vecs_path, sing_vals_path, R_sing_vecs_path)
        if parallel.is_rank_zero():
            L_sing_vecs_loaded = util.load_mat_text(L_sing_vecs_path)
            R_sing_vecs_loaded = util.load_mat_text(R_sing_vecs_path)
            sing_vals_loaded = N.squeeze(N.array(util.load_mat_text(
                sing_vals_path)))
            hankel_mat_loaded = util.load_mat_text(hankel_mat_path)
        else:
            L_sing_vecs_loaded = None
            R_sing_vecs_loaded = None
            sing_vals_loaded = None
            hankel_mat_loaded = None

        if parallel.is_distributed():
            L_sing_vecs_loaded = parallel.comm.bcast(L_sing_vecs_loaded, root=0)
            R_sing_vecs_loaded = parallel.comm.bcast(R_sing_vecs_loaded, root=0)
            sing_vals_loaded = parallel.comm.bcast(sing_vals_loaded, root=0)
            hankel_mat_loaded = parallel.comm.bcast(hankel_mat_loaded, root=0)
        
        N.testing.assert_array_almost_equal(self.bpod.hankel_mat,
          self.hankel_mat_true, decimal=tol)
        N.testing.assert_array_almost_equal(self.bpod.L_sing_vecs,
          self.L_sing_vecs_true, decimal=tol)
        N.testing.assert_array_almost_equal(self.bpod.R_sing_vecs,
          self.R_sing_vecs_true, decimal=tol)
        N.testing.assert_array_almost_equal(self.bpod.sing_vals,
          self.sing_vals_true, decimal=tol)
          
        N.testing.assert_array_almost_equal(hankel_mat_loaded,
          self.hankel_mat_true, decimal=tol)
        N.testing.assert_array_almost_equal(L_sing_vecs_loaded,
          self.L_sing_vecs_true, decimal=tol)
        N.testing.assert_array_almost_equal(R_sing_vecs_loaded,
          self.R_sing_vecs_true, decimal=tol)
        N.testing.assert_array_almost_equal(sing_vals_loaded,
          self.sing_vals_true, decimal=tol)
        

    def test_compute_modes(self):
        """
        Test computing modes in serial and parallel. 
        
        This method uses the existing random data set saved to disk. It tests
        that BPOD can generate the modes, save them, and load them, then
        compares them to the known solution.
        """

        direct_mode_path = 'files_modaldecomp_test/direct_mode_%03d.txt'
        adjoint_mode_path = 'files_modaldecomp_test/adjoint_mode_%03d.txt'
        
        # starts with the CORRECT decomposition.
        self.bpod.R_sing_vecs = self.R_sing_vecs_true
        self.bpod.L_sing_vecs = self.L_sing_vecs_true
        self.bpod.sing_vals = self.sing_vals_true
        
        self.bpod.compute_direct_modes(self.mode_nums, direct_mode_path,
          index_from=self.index_from, direct_snap_paths=self.direct_snap_paths)
          
        self.bpod.compute_adjoint_modes(self.mode_nums, adjoint_mode_path,
          index_from=self.index_from, adjoint_snap_paths=self.adjoint_snap_paths)
          
        for mode_num in self.mode_nums:
            if parallel.is_rank_zero():
                direct_mode = util.load_mat_text(direct_mode_path % mode_num)
                adjoint_mode = util.load_mat_text(adjoint_mode_path % mode_num)
            else:
                direct_mode = None
                adjoint_mode = None
            if parallel.is_distributed():
                direct_mode = parallel.comm.bcast(direct_mode, root=0)
                adjoint_mode = parallel.comm.bcast(adjoint_mode, root=0)
            N.testing.assert_array_almost_equal(direct_mode, self.direct_mode_mat[:,
                mode_num-self.index_from])
            N.testing.assert_array_almost_equal(adjoint_mode, self.\
                adjoint_mode_mat[:,mode_num-self.index_from])
        
        if parallel.is_rank_zero():
            for mode_num1 in self.mode_nums:
                direct_mode = util.load_mat_text(
                  direct_mode_path%mode_num1)
                for mode_num2 in self.mode_nums:
                    adjoint_mode = util.load_mat_text(
                      adjoint_mode_path%mode_num2)
                    IP = self.bpod.field_ops.inner_product(
                      direct_mode,adjoint_mode)
                    if mode_num1 != mode_num2:
                        self.assertAlmostEqual(IP, 0.)
                    else:
                        self.assertAlmostEqual(IP, 1.)
      
if __name__=='__main__':
    unittest.main(verbosity=2)
    
        
    


