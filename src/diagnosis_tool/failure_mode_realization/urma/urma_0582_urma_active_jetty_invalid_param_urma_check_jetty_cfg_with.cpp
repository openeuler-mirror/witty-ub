#include "urma_0582_urma_active_jetty_invalid_param_urma_check_jetty_cfg_with.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0582UrmaActiveJettyInvalidParamUrmaCheckJettyCfgWith> g_urma("urma_0582");

bool Urma0582UrmaActiveJettyInvalidParamUrmaCheckJettyCfgWith::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0582UrmaActiveJettyInvalidParamUrmaCheckJettyCfgWith::GetName() const
{
    return "urma_active_jetty 参数非法（urma_check_jetty_cfg_with_jetty_grp(cfg) != 0）";
}

std::string Urma0582UrmaActiveJettyInvalidParamUrmaCheckJettyCfgWith::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `urma_check_jetty_cfg_with_jetty_grp(cfg) != 0`；该路径返回 URMA_EINVAL";
}

RootCause Urma0582UrmaActiveJettyInvalidParamUrmaCheckJettyCfgWith::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0582UrmaActiveJettyInvalidParamUrmaCheckJettyCfgWith::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0582UrmaActiveJettyInvalidParamUrmaCheckJettyCfgWith::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0582UrmaActiveJettyInvalidParamUrmaCheckJettyCfgWith::GetId() const
{
    return "urma_0582";
}
} // namespace diag
