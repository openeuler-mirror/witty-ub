#include "urma_0049_init_create_jetty_cmd_invalid_param_cfg_jfs_cfg_jfc.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0049InitCreateJettyCmdInvalidParamCfgJfsCfgJfc> g_urma("urma_0049");

bool Urma0049InitCreateJettyCmdInvalidParamCfgJfsCfgJfc::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0049InitCreateJettyCmdInvalidParamCfgJfsCfgJfc::GetName() const
{
    return "init_create_jetty_cmd 参数非法（cfg->jfs_cfg.jfc == NULL）";
}

std::string Urma0049InitCreateJettyCmdInvalidParamCfgJfsCfgJfc::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `cfg->jfs_cfg.jfc == NULL`；该路径返回 -1";
}

RootCause Urma0049InitCreateJettyCmdInvalidParamCfgJfsCfgJfc::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0049InitCreateJettyCmdInvalidParamCfgJfsCfgJfc::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0049InitCreateJettyCmdInvalidParamCfgJfsCfgJfc::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0049InitCreateJettyCmdInvalidParamCfgJfsCfgJfc::GetId() const
{
    return "urma_0049";
}
} // namespace diag
