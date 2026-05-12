#include "urma_0653_urma_create_jetty_check_jfc_invalid_param_jetty_cfg_jfs.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0653UrmaCreateJettyCheckJfcInvalidParamJettyCfgJfs> g_urma("urma_0653");

bool Urma0653UrmaCreateJettyCheckJfcInvalidParamJettyCfgJfs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, jfc is NULL in jfs_cfg."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0653UrmaCreateJettyCheckJfcInvalidParamJettyCfgJfs::GetName() const
{
    return "urma_create_jetty_check_jfc 参数非法（jetty_cfg->jfs_cfg.jfc == NULL）";
}

std::string Urma0653UrmaCreateJettyCheckJfcInvalidParamJettyCfgJfs::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty_cfg->jfs_cfg.jfc == NULL`；该路径返回 -1";
}

RootCause Urma0653UrmaCreateJettyCheckJfcInvalidParamJettyCfgJfs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0653UrmaCreateJettyCheckJfcInvalidParamJettyCfgJfs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0653UrmaCreateJettyCheckJfcInvalidParamJettyCfgJfs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, jfc is NULL in jfs_cfg.";
}

std::string Urma0653UrmaCreateJettyCheckJfcInvalidParamJettyCfgJfs::GetId() const
{
    return "urma_0653";
}
} // namespace diag
