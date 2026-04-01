"""Grouped UI retranslations extracted from the main window."""

from __future__ import annotations

from .i18n import tr


def retranslate_mod_manager(window) -> None:
    if hasattr(window, "mm_title_lbl"):
        window.mm_title_lbl.setText(tr("mod_manager.title"))
    if hasattr(window, "mm_info_lbl"):
        window.mm_info_lbl.setText(tr("mod_manager.info"))
    if hasattr(window, "mm_paths_hint"):
        window.mm_paths_hint.setText(tr("mod_manager.paths_moved_info"))
    if getattr(window, "mm_linux_cmd_box", None) is not None:
        window.mm_linux_cmd_box.setTitle(tr("mod_manager.linux_cmd_label"))
    if hasattr(window, "mm_linux_cmd_edit"):
        window.mm_linux_cmd_edit.setPlaceholderText(tr("mod_manager.linux_cmd_placeholder"))
        window.mm_linux_cmd_edit.setToolTip(tr("mod_manager.linux_cmd_hint"))
    if hasattr(window, "gs_mod_paths_box"):
        window.gs_mod_paths_box.setTitle(tr("mod_manager.paths_group"))
    if hasattr(window, "gs_repo_lbl"):
        window.gs_repo_lbl.setText(tr("mod_manager.repo_label"))
    if hasattr(window, "gs_repo_browse_btn"):
        window.gs_repo_browse_btn.setText(tr("welcome.browse"))
    if hasattr(window, "gs_repo_multi_lbl"):
        window.gs_repo_multi_lbl.setText(tr("mod_manager.repo_multi_label"))
    if hasattr(window, "gs_repo_multi_hint_lbl"):
        window.gs_repo_multi_hint_lbl.setText(tr("mod_manager.repo_multi_hint"))
    if hasattr(window, "gs_flmm_lbl"):
        window.gs_flmm_lbl.setText(tr("mod_manager.flmm_install_label"))
    if hasattr(window, "gs_flmm_browse_btn"):
        window.gs_flmm_browse_btn.setText(tr("welcome.browse"))
    if hasattr(window, "gs_flmm_detect_btn"):
        window.gs_flmm_detect_btn.setText(tr("mod_manager.flmm_detect"))
    if hasattr(window, "mm_direct_lbl"):
        window.mm_direct_lbl.setText(tr("mod_manager.section.direct_mods"))
    if hasattr(window, "mm_repo_lbl"):
        window.mm_repo_lbl.setText(tr("mod_manager.section.mods"))
    if hasattr(window, "mm_target_line_lbl"):
        window._mod_manager_update_target_inline_label()
    if hasattr(window, "mm_table"):
        window.mm_table.setHorizontalHeaderLabels(
            [tr("mod_manager.col.name"), tr("mod_manager.col.type"), tr("mod_manager.col.source"), tr("mod_manager.col.version"), tr("mod_manager.col.status")]
        )
    if hasattr(window, "mm_new_repo_btn"):
        window.mm_new_repo_btn.setText(tr("mod_manager.btn.new_mod"))
    if hasattr(window, "mm_add_direct_btn"):
        window.mm_add_direct_btn.setText(tr("mod_manager.btn.add_direct"))
    if hasattr(window, "mm_create_install_from_mod_btn"):
        window.mm_create_install_from_mod_btn.setText(tr("mod_manager.btn.create_install_from_mod"))
    if hasattr(window, "mm_delete_btn"):
        window.mm_delete_btn.setText(tr("mod_manager.btn.delete"))
    if hasattr(window, "mm_open_folder_btn"):
        window.mm_open_folder_btn.setText(tr("mod_manager.btn.open_folder"))
    if hasattr(window, "mm_open_saves_btn"):
        window.mm_open_saves_btn.setText(tr("mod_manager.btn.open_savegames"))
    if hasattr(window, "mm_edit_ctx_btn"):
        window.mm_edit_ctx_btn.setText(tr("mod_manager.btn.open_for_editing"))
    if hasattr(window, "mm_clear_edit_ctx_btn"):
        window.mm_clear_edit_ctx_btn.setText(tr("mod_manager.btn.clear_editing"))
    if hasattr(window, "mm_opensp_cb"):
        window.mm_opensp_cb.setText(tr("mod_manager.opensp.enable_for_mod"))
    if hasattr(window, "mm_edit_sp_ship_btn"):
        window.mm_edit_sp_ship_btn.setText(tr("mod_manager.btn.edit_sp_ship"))
    if hasattr(window, "mm_activate_btn"):
        window.mm_activate_btn.setText(tr("mod_manager.btn.activate"))
    if hasattr(window, "mm_deactivate_btn"):
        window.mm_deactivate_btn.setText(tr("mod_manager.btn.deactivate"))
    if hasattr(window, "mm_repair_btn"):
        window.mm_repair_btn.setText(window._mod_manager_repair_caption())
    if hasattr(window, "mm_launch_btn"):
        window.mm_launch_btn.setText(tr("mod_manager.btn.launch_fl"))
    if hasattr(window, "header_launch_fl_btn"):
        window.header_launch_fl_btn.setText(tr("mod_manager.btn.launch_fl"))
        window.header_launch_fl_btn.setToolTip(tr("mod_manager.tip.launch_fl"))
    if hasattr(window, "mm_launch_apply_res_cb"):
        window.mm_launch_apply_res_cb.setText(tr("mod_manager.launch.apply_resolution"))
    if hasattr(window, "mm_launch_ratio_lbl"):
        window.mm_launch_ratio_lbl.setText(tr("mod_manager.launch.ratio_label"))
    if hasattr(window, "mm_launch_res_lbl"):
        window.mm_launch_res_lbl.setText(tr("mod_manager.launch.resolution_label"))
    if hasattr(window, "mm_launch_depth_cb"):
        window.mm_launch_depth_cb.setText(tr("mod_manager.launch.set_color_depth_32"))
    if hasattr(window, "mm_refresh_btn"):
        window.mm_refresh_btn.setText(tr("mod_manager.ctx.refresh"))
    if hasattr(window, "mm_profile_header_lbl"):
        profile = window._mod_manager_selected_profile()
        if isinstance(profile, dict):
            window.mm_profile_header_lbl.setText(
                tr("mod_manager.selected_profile_header").format(name=str(profile.get("name", "") or "").strip())
            )
        else:
            window.mm_profile_header_lbl.setText(tr("mod_manager.selected_profile_none"))
    if hasattr(window, "mm_set_target_btn"):
        window.mm_set_target_btn.setText(tr("mod_manager.btn.set_target_installation"))
    if hasattr(window, "mm_setup_notice_lbl"):
        window._mod_manager_update_setup_notice()
    window._mod_manager_apply_tooltips()


def retranslate_mod_settings(window) -> None:
    if hasattr(window, "mod_settings_title_lbl"):
        window.mod_settings_title_lbl.setText(tr("mod_settings.title"))
    if hasattr(window, "mod_settings_info_lbl"):
        window.mod_settings_info_lbl.setText(tr("mod_settings.info"))
    if hasattr(window, "mod_settings_exe_path_box"):
        window.mod_settings_exe_path_box.setTitle(tr("mod_settings.exe_path_group"))
    if hasattr(window, "mod_settings_exe_path_info_lbl"):
        window.mod_settings_exe_path_info_lbl.setText(tr("mod_settings.exe_path_info"))
    if hasattr(window, "mod_settings_edit_config_link"):
        window.mod_settings_edit_config_link.setText(tr("mod_settings.link.edit_config"))
    if hasattr(window, "mod_settings_exe_path_resolved_lbl"):
        window.mod_settings_exe_path_resolved_lbl.setText("")
    if hasattr(window, "mod_settings_exe_path_browse_btn"):
        window.mod_settings_exe_path_browse_btn.setText(tr("welcome.browse"))
    if hasattr(window, "mod_settings_exe_path_save_btn"):
        window.mod_settings_exe_path_save_btn.setText(tr("mod_settings.btn.save_exe_path"))
    if hasattr(window, "mod_settings_versions_box"):
        window.mod_settings_versions_box.setTitle(tr("mod_settings.versions_group"))
    if hasattr(window, "mod_settings_offsets_box"):
        window.mod_settings_offsets_box.setTitle(tr("mod_settings.offsets_group"))
    if hasattr(window, "mod_settings_reload_btn"):
        window.mod_settings_reload_btn.setText(tr("mod_settings.btn.reload"))
    if hasattr(window, "mod_settings_apply_btn"):
        window.mod_settings_apply_btn.setText(tr("mod_settings.btn.apply_offsets"))
    for btn in getattr(window, "mod_settings_version_buttons", {}).values():
        btn.setText(tr("mod_settings.btn.apply_version"))
    for btn in getattr(window, "mod_settings_launch_buttons", {}).values():
        btn.setText(tr("mod_settings.btn.launch_exe"))
    if hasattr(window, "mod_settings_offset_table"):
        window.mod_settings_offset_table.setHorizontalHeaderLabels(
            [
                tr("mod_settings.col.setting"),
                tr("mod_settings.col.exe"),
                tr("mod_settings.col.offset"),
                tr("mod_settings.col.type"),
                tr("mod_settings.col.current"),
                tr("mod_settings.col.new"),
                tr("mod_settings.col.notes"),
            ]
        )
    if hasattr(window, "mod_settings_page"):
        window._mod_settings_refresh()


def retranslate_welcome_and_settings(window) -> None:
    if hasattr(window, "welcome_title_lbl"):
        window.welcome_title_lbl.setText(tr("welcome.title"))
    if hasattr(window, "welcome_settings_grp"):
        window.welcome_settings_grp.setTitle(tr("welcome.settings_group"))
    if hasattr(window, "welcome_intro_grp"):
        window.welcome_intro_grp.setTitle(tr("welcome.intro_group"))
    if hasattr(window, "welcome_intro_lbl"):
        window.welcome_intro_lbl.setText(tr("welcome.intro_text"))
    if hasattr(window, "welcome_next_title_lbl"):
        window.welcome_next_title_lbl.setText(tr("welcome.next_title"))
    if hasattr(window, "welcome_next_steps_lbl"):
        window.welcome_next_steps_lbl.setText(tr("welcome.next_steps"))
    if hasattr(window, "welcome_lang_lbl"):
        window.welcome_lang_lbl.setText(tr("welcome.lang_label"))
    if hasattr(window, "welcome_theme_lbl"):
        window.welcome_theme_lbl.setText(tr("welcome.theme_label"))
    if hasattr(window, "welcome_update_check_lbl"):
        window.welcome_update_check_lbl.setText(tr("settings.update_check_label"))
    if hasattr(window, "welcome_update_check_cb"):
        window.welcome_update_check_cb.setText(tr("settings.update_check_enabled"))
    if hasattr(window, "welcome_help_btn"):
        window.welcome_help_btn.setText(tr("welcome.help"))
    if hasattr(window, "welcome_install_tools_btn"):
        window.welcome_install_tools_btn.setText(tr("welcome.install_ids_tools"))
    if hasattr(window, "welcome_continue_btn"):
        window.welcome_continue_btn.setText(tr("welcome.continue_mod_manager"))
    window._refresh_welcome_ids_toolchain_notice()

    if hasattr(window, "gs_title_lbl"):
        window.gs_title_lbl.setText(window._global_settings_caption())
    if hasattr(window, "gs_info_lbl"):
        window.gs_info_lbl.setText(tr("settings.global_info"))
    if hasattr(window, "gs_tabs"):
        i_general = window.gs_tabs.indexOf(getattr(window, "gs_general_tab", None))
        i_system = window.gs_tabs.indexOf(getattr(window, "gs_system_editor_tab", None))
        i_mod = window.gs_tabs.indexOf(getattr(window, "gs_mod_manager_tab", None))
        i_editors = window.gs_tabs.indexOf(getattr(window, "gs_editors_tab", None))
        i_dev = window.gs_tabs.indexOf(getattr(window, "gs_dev_status_tab", None))
        if i_general >= 0:
            window.gs_tabs.setTabText(i_general, tr("settings.tab.general"))
        if i_system >= 0:
            window.gs_tabs.setTabText(i_system, tr("settings.tab.system_editor"))
        if i_mod >= 0:
            window.gs_tabs.setTabText(i_mod, tr("settings.tab.mod_manager"))
        if i_editors >= 0:
            window.gs_tabs.setTabText(i_editors, tr("settings.tab.editors"))
        if i_dev >= 0:
            window.gs_tabs.setTabText(i_dev, tr("settings.tab.dev_status"))
    if hasattr(window, "gs_system_editor_info_lbl"):
        window.gs_system_editor_info_lbl.setText(tr("settings.system_editor_info"))
    if hasattr(window, "gs_xml_editor_box"):
        window.gs_xml_editor_box.setTitle(tr("settings.system_editor_xml_group"))
    if hasattr(window, "gs_xml_editor_path_lbl"):
        window.gs_xml_editor_path_lbl.setText(tr("settings.system_editor_xml_editor"))
    if hasattr(window, "gs_xml_editor_hint_lbl"):
        window.gs_xml_editor_hint_lbl.setText(tr("settings.system_editor_xml_hint"))
    if hasattr(window, "gs_xml_editor_browse_btn"):
        window.gs_xml_editor_browse_btn.setText(tr("welcome.browse"))
    if hasattr(window, "gs_mm_placeholder_lbl"):
        window.gs_mm_placeholder_lbl.setText(tr("settings.mod_manager_placeholder"))
    if hasattr(window, "gs_editors_info_lbl"):
        window.gs_editors_info_lbl.setText(tr("settings.editors_info"))
    if hasattr(window, "gs_savegame_box"):
        window.gs_savegame_box.setTitle(tr("settings.savegame_group"))
    if hasattr(window, "gs_savegame_editor_path_lbl"):
        window.gs_savegame_editor_path_lbl.setText(tr("settings.savegame_editor_path"))
    if hasattr(window, "gs_savegame_repo_lbl"):
        window.gs_savegame_repo_lbl.setText(tr("settings.savegame_repo_label"))
    if hasattr(window, "gs_savegame_status_lbl"):
        window._refresh_savegame_editor_status()
    if hasattr(window, "gs_savegame_info_lbl"):
        window.gs_savegame_info_lbl.setText(tr("settings.savegame_info"))
    if hasattr(window, "gs_savegame_editor_browse"):
        window.gs_savegame_editor_browse.setText(tr("welcome.browse"))
    if hasattr(window, "gs_savegame_repo_btn"):
        window.gs_savegame_repo_btn.setText(tr("settings.savegame_repo_open"))
    if hasattr(window, "gs_savegame_check_btn"):
        window.gs_savegame_check_btn.setText(tr("settings.savegame_check_updates"))
    if hasattr(window, "gs_savegame_install_btn"):
        window.gs_savegame_install_btn.setText(tr("settings.savegame_install_update"))
    if hasattr(window, "gs_dev_status_info_lbl"):
        window.gs_dev_status_info_lbl.setText(tr("dev_status.info"))
    if hasattr(window, "gs_dev_states_box"):
        window.gs_dev_states_box.setTitle(tr("dev_status.states_title"))
    if hasattr(window, "gs_dev_table"):
        window.gs_dev_table.setHorizontalHeaderLabels(
            [tr("dev_status.col.nav"), tr("dev_status.col.status"), tr("dev_status.col.details")]
        )
    if hasattr(window, "gs_bini_box"):
        window.gs_bini_box.setTitle(tr("settings.bini_group"))
    if hasattr(window, "gs_ids_toolchain_box"):
        window.gs_ids_toolchain_box.setTitle(tr("settings.ids_toolchain_group"))
    if hasattr(window, "gs_ids_toolchain_path_lbl"):
        window.gs_ids_toolchain_path_lbl.setText(tr("settings.ids_toolchain_path"))
    if hasattr(window, "gs_ids_toolchain_info_lbl"):
        window.gs_ids_toolchain_info_lbl.setText(tr("settings.ids_toolchain_info"))
    if hasattr(window, "gs_ids_toolchain_browse_btn"):
        window.gs_ids_toolchain_browse_btn.setText(tr("welcome.browse"))
    if hasattr(window, "gs_ids_toolchain_help_btn"):
        window.gs_ids_toolchain_help_btn.setText("?")
        window.gs_ids_toolchain_help_btn.setToolTip(tr("settings.ids_toolchain_help_tip"))
    if hasattr(window, "gs_dll_debug_box"):
        window.gs_dll_debug_box.setTitle(tr("settings.dll_debug_group"))
    if hasattr(window, "gs_dll_debug_info_lbl"):
        window.gs_dll_debug_info_lbl.setText(tr("settings.dll_debug_info"))
    if hasattr(window, "gs_dll_debug_refresh_btn"):
        window.gs_dll_debug_refresh_btn.setText(tr("settings.dll_debug_refresh"))
    if hasattr(window, "gs_bini_path_lbl"):
        window.gs_bini_path_lbl.setText(tr("settings.bini_path"))
    if hasattr(window, "gs_bini_info_lbl"):
        window.gs_bini_info_lbl.setText(tr("settings.bini_info"))
    if hasattr(window, "gs_bini_convert_btn"):
        window.gs_bini_convert_btn.setText(tr("settings.bini_convert"))
    if hasattr(window, "gs_lang_lbl"):
        window.gs_lang_lbl.setText(tr("welcome.lang_label"))
    if hasattr(window, "gs_theme_lbl"):
        window.gs_theme_lbl.setText(tr("welcome.theme_label"))
    if hasattr(window, "gs_auto_name_lang_lbl"):
        window.gs_auto_name_lang_lbl.setText(tr("settings.auto_name_lang_label"))
    if hasattr(window, "gs_update_check_lbl"):
        window.gs_update_check_lbl.setText(tr("settings.update_check_label"))
    if hasattr(window, "gs_update_check_cb"):
        window.gs_update_check_cb.setText(tr("settings.update_check_enabled"))
    if hasattr(window, "gs_update_prerelease_lbl"):
        window.gs_update_prerelease_lbl.setText(tr("settings.update_prerelease_label"))
    if hasattr(window, "gs_update_prerelease_cb"):
        window.gs_update_prerelease_cb.setText(tr("settings.update_prerelease_enabled"))
        allow_pre_toggle = window._updates_allow_prerelease_toggle()
        window.gs_update_prerelease_lbl.setVisible(allow_pre_toggle)
        window.gs_update_prerelease_cb.setVisible(allow_pre_toggle)
    if hasattr(window, "gs_show_splash_lbl"):
        window.gs_show_splash_lbl.setText(tr("settings.show_splash_label"))
    if hasattr(window, "gs_show_splash_cb"):
        window.gs_show_splash_cb.setText(tr("settings.show_splash_enabled"))
    if hasattr(window, "gs_auto_name_lang_cb"):
        cur = window.gs_auto_name_lang_cb.currentData()
        window.gs_auto_name_lang_cb.setItemText(0, tr("settings.auto_name_lang.de"))
        window.gs_auto_name_lang_cb.setItemText(1, tr("settings.auto_name_lang.en"))
        ai = window.gs_auto_name_lang_cb.findData(cur)
        if ai >= 0:
            window.gs_auto_name_lang_cb.setCurrentIndex(ai)
    if hasattr(window, "gs_bini_target_browse"):
        window.gs_bini_target_browse.setText(tr("welcome.browse"))
    if hasattr(window, "gs_freelancer_ini_btn"):
        window.gs_freelancer_ini_btn.setText(tr("settings.freelancer_ini_editor"))
    if hasattr(window, "gs_apply_btn"):
        window.gs_apply_btn.setText(tr("settings.apply"))
    if hasattr(window, "gs_mm_apply_btn"):
        window.gs_mm_apply_btn.setText(tr("settings.apply"))
    if hasattr(window, "gs_dll_debug_text"):
        window._refresh_dll_debug_view()
    window._refresh_dev_status_page()


def retranslate_trade_name_and_ini(window) -> None:
    if hasattr(window, "trade_sidebar_new_btn"):
        window.trade_sidebar_new_btn.setText(tr("trade.btn.create"))
    if hasattr(window, "trade_sidebar_edit_btn"):
        window.trade_sidebar_edit_btn.setText(tr("trade.btn.edit"))
    if hasattr(window, "trade_sidebar_delete_btn"):
        window.trade_sidebar_delete_btn.setText(tr("trade.btn.delete"))
    if hasattr(window, "trade_sidebar_visualize_btn"):
        window.trade_sidebar_visualize_btn.setText(tr("trade.btn.visualize"))
    if hasattr(window, "trade_sidebar_title_lbl"):
        window.trade_sidebar_title_lbl.setText(tr("trade.sidebar.title"))
    if hasattr(window, "trade_sidebar_info_lbl"):
        window.trade_sidebar_info_lbl.setText(tr("trade.sidebar.info"))
    if hasattr(window, "name_sidebar_title_lbl"):
        window.name_sidebar_title_lbl.setText(tr("name.sidebar.title"))
    if hasattr(window, "name_sidebar_info_lbl"):
        window.name_sidebar_info_lbl.setText(tr("name.sidebar.info"))
    if hasattr(window, "name_reload_btn"):
        window.name_reload_btn.setText(tr("name.btn.reload"))
    if hasattr(window, "name_create_btn"):
        window.name_create_btn.setText(tr("name.btn.create"))
    if hasattr(window, "name_update_btn"):
        window.name_update_btn.setText(tr("name.btn.update"))
    if hasattr(window, "name_conflicts_btn"):
        window.name_conflicts_btn.setText(tr("name.btn.conflicts"))
    if hasattr(window, "name_assign_btn"):
        window.name_assign_btn.setText(tr("name.btn.assign_missing"))
    if hasattr(window, "name_info_validate_btn"):
        window.name_info_validate_btn.setText(tr("info.btn.validate"))
    if hasattr(window, "name_info_create_btn"):
        window.name_info_create_btn.setText(tr("info.btn.create"))
    if hasattr(window, "name_info_update_btn"):
        window.name_info_update_btn.setText(tr("info.btn.update"))
    if hasattr(window, "trade_filter_commodity_lbl"):
        window.trade_filter_commodity_lbl.setText(tr("trade.filter.commodity"))
    if hasattr(window, "trade_filter_min_profit_lbl"):
        window.trade_filter_min_profit_lbl.setText(tr("trade.filter.min_profit"))
    if hasattr(window, "trade_filter_same_system_cb"):
        window.trade_filter_same_system_cb.setText(tr("trade.filter.same_system"))
    if hasattr(window, "trade_filter_search"):
        window.trade_filter_search.setPlaceholderText(tr("trade.filter.search_ph"))
    if hasattr(window, "trade_filter_apply_btn"):
        window.trade_filter_apply_btn.setText(tr("trade.filter.apply"))
    if hasattr(window, "trade_filter_max_jumps_lbl"):
        window.trade_filter_max_jumps_lbl.setText(tr("trade.filter.max_jumps"))
    if hasattr(window, "trade_filter_source_system_lbl"):
        window.trade_filter_source_system_lbl.setText(tr("trade.filter.source_system"))
    if hasattr(window, "trade_filter_target_system_lbl"):
        window.trade_filter_target_system_lbl.setText(tr("trade.filter.target_system"))
    if hasattr(window, "trade_title_lbl"):
        window.trade_title_lbl.setText(tr("trade.title"))
    if hasattr(window, "trade_subtitle_lbl"):
        window.trade_subtitle_lbl.setText(tr("trade.subtitle"))
    if hasattr(window, "ini_title_lbl"):
        window.ini_title_lbl.setText(tr("ini.title"))
        window.ini_subtitle_lbl.setText(tr("ini.subtitle"))
        window.ini_root_lbl.setText(tr("ini.root"))
        window.ini_reload_btn.setText(tr("ini.btn.reload_tree"))
        window.ini_save_btn.setText(tr("ini.btn.save"))
    if hasattr(window, "_ini_model_preview_open_btn"):
        window._ini_model_preview_open_btn.setText(tr("ini.model.open_preview"))
    if hasattr(window, "_ini_model_preview_manager_btn"):
        window._ini_model_preview_manager_btn.setText(tr("ini.model.open_manager"))
    if hasattr(window, "name_title_lbl"):
        window.name_title_lbl.setText(tr("name.title"))
    if hasattr(window, "name_subtitle_lbl"):
        window.name_subtitle_lbl.setText(tr("name.subtitle"))
    if hasattr(window, "name_subnav_name_btn"):
        window.name_subnav_name_btn.setText(tr("name.tab.names"))
    if hasattr(window, "name_subnav_info_btn"):
        window.name_subnav_info_btn.setText(tr("name.tab.info"))
    if hasattr(window, "name_search_lbl"):
        window.name_search_lbl.setText(tr("name.search"))
    if hasattr(window, "name_search_edit"):
        window.name_search_edit.setPlaceholderText(tr("name.search.placeholder"))
    if hasattr(window, "name_clear_filters_btn"):
        window.name_clear_filters_btn.setText(tr("name.btn.clear_filters"))
    if hasattr(window, "name_reload_page_btn"):
        window.name_reload_page_btn.setText(tr("name.btn.reload"))
    if hasattr(window, "name_conflicts_page_btn"):
        window.name_conflicts_page_btn.setText(tr("name.btn.conflicts"))
    if hasattr(window, "name_ids_table"):
        window.name_ids_table.setHorizontalHeaderLabels(
            [tr("name.col.id"), tr("name.col.text"), tr("name.col.dll"), tr("name.col.editable")]
        )
    if hasattr(window, "name_selected_id_lbl"):
        window.name_selected_id_lbl.setText(tr("name.selected_id"))
    if hasattr(window, "name_text_lbl"):
        window.name_text_lbl.setText(tr("name.text"))
    if hasattr(window, "name_update_page_btn"):
        window.name_update_page_btn.setText(tr("name.btn.update"))
    if hasattr(window, "name_create_page_btn"):
        window.name_create_page_btn.setText(tr("name.btn.create"))
    if hasattr(window, "name_jump_page_btn"):
        window.name_jump_page_btn.setText(tr("btn.jump"))
    if hasattr(window, "name_usage_title_lbl"):
        window.name_usage_title_lbl.setText(tr("name.usage.title"))
    if hasattr(window, "name_usage_table"):
        window.name_usage_table.setHorizontalHeaderLabels(
            [tr("name.col.system"), tr("name.col.section"), tr("name.col.nickname"), tr("name.col.archetype"), tr("name.col.file")]
        )
    if hasattr(window, "name_missing_title_lbl"):
        window.name_missing_title_lbl.setText(tr("name.missing.title"))
    if hasattr(window, "name_missing_table"):
        window.name_missing_table.setHorizontalHeaderLabels(
            [tr("name.col.system"), tr("name.col.section"), tr("name.col.nickname"), tr("name.col.archetype"), tr("name.col.file")]
        )
    if hasattr(window, "name_missing_text_lbl"):
        window.name_missing_text_lbl.setText(tr("name.assign_text"))
    if hasattr(window, "name_assign_page_btn"):
        window.name_assign_page_btn.setText(tr("name.btn.assign_missing"))
    if hasattr(window, "info_editor_subtitle_lbl"):
        window.info_editor_subtitle_lbl.setText(tr("info.subtitle"))
    if hasattr(window, "info_search_lbl"):
        window.info_search_lbl.setText(tr("info.search"))
    if hasattr(window, "info_search_edit"):
        window.info_search_edit.setPlaceholderText(tr("info.search.placeholder"))
    if hasattr(window, "info_reload_btn"):
        window.info_reload_btn.setText(tr("info.btn.reload"))
    if hasattr(window, "info_builder_format_lbl"):
        window.info_builder_format_lbl.setText(tr("info.builder.field.format"))
    if hasattr(window, "info_builder_color_lbl"):
        window.info_builder_color_lbl.setText(tr("info.builder.field.color"))
    if hasattr(window, "info_fmt_bold_btn"):
        window.info_fmt_bold_btn.setText(tr("info.builder.btn.bold"))
    if hasattr(window, "info_fmt_italic_btn"):
        window.info_fmt_italic_btn.setText(tr("info.builder.btn.italic"))
    if hasattr(window, "info_fmt_underline_btn"):
        window.info_fmt_underline_btn.setText(tr("info.builder.btn.underline"))
    if hasattr(window, "info_fmt_align_left_btn"):
        window.info_fmt_align_left_btn.setText(tr("info.builder.btn.align_left"))
    if hasattr(window, "info_fmt_align_center_btn"):
        window.info_fmt_align_center_btn.setText(tr("info.builder.btn.align_center"))
    if hasattr(window, "info_fmt_align_right_btn"):
        window.info_fmt_align_right_btn.setText(tr("info.builder.btn.align_right"))
    if hasattr(window, "info_builder_color_pick_btn"):
        window.info_builder_color_pick_btn.setText(tr("info.builder.btn.color_pick"))
    if hasattr(window, "info_builder_color_reset_btn"):
        window.info_builder_color_reset_btn.setText(tr("info.builder.btn.color_default"))
    if hasattr(window, "info_ids_table"):
        window.info_ids_table.setHorizontalHeaderLabels(
            [tr("info.col.id"), tr("info.col.preview"), tr("info.col.dll"), tr("info.col.editable")]
        )
    if hasattr(window, "info_selected_id_lbl"):
        window.info_selected_id_lbl.setText(tr("info.selected_id"))
    if hasattr(window, "info_dll_lbl"):
        window.info_dll_lbl.setText(tr("info.source_dll"))
    if hasattr(window, "info_xml_lbl"):
        window.info_xml_lbl.setText(tr("info.xml"))
    if hasattr(window, "info_preview_lbl"):
        window.info_preview_lbl.setText(tr("info.preview"))
    if hasattr(window, "info_validate_btn"):
        window.info_validate_btn.setText(tr("info.btn.validate"))
    if hasattr(window, "info_create_btn"):
        window.info_create_btn.setText(tr("info.btn.create"))
    if hasattr(window, "info_update_btn"):
        window.info_update_btn.setText(tr("info.btn.update"))
    if hasattr(window, "info_jump_btn"):
        window.info_jump_btn.setText(tr("btn.jump"))
    if hasattr(window, "info_note_lbl"):
        window.info_note_lbl.setText(tr("info.note"))
