#include "urma_0659_urma_create_jetty_check_trans_mode_invalid_param_urma_check.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0659UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck> g_urma("urma_0659");

bool Urma0659UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, trans_mode: %, order_type: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0659UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck::GetName() const
{
    return "urma_create_jetty_check_trans_mode 参数非法（urma_check_order_type(jetty_cfg->jfs_cfg.trans_mode, "
           "order_type) != 0）";
}

std::string Urma0659UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `urma_check_order_type(jetty_cfg->jfs_cfg.trans_mode, order_type) != "
           "0`；该路径返回 -1";
}

RootCause Urma0659UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0659UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0659UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, trans_mode: %, order_type: %.";
}

std::string Urma0659UrmaCreateJettyCheckTransModeInvalidParamUrmaCheck::GetId() const
{
    return "urma_0659";
}
} // namespace diag
