#include "urma_0657_urma_create_jetty_check_trans_mode_invalid_param_urma_check.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0657UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck> g_urma("urma_0657");

bool Urma0657UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, trans_mode: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0657UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck::GetName() const
{
    return "urma_create_jetty_check_trans_mode 参数非法（urma_check_trans_mode_valid(jetty_cfg->jfs_cfg.trans_mode) != "
           "true）";
}

std::string Urma0657UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `urma_check_trans_mode_valid(jetty_cfg->jfs_cfg.trans_mode) != "
           "true`；该路径返回 -1";
}

RootCause Urma0657UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0657UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0657UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, trans_mode: %.";
}

std::string Urma0657UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck::GetId() const
{
    return "urma_0657";
}
} // namespace diag
