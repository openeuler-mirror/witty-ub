#include "urma_0604_urma_advise_jetty_invalid_param_jetty_null_tjetty_null_tjetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0604UrmaAdviseJettyInvalidParamJettyNullTjettyNullTjetty> g_urma("urma_0604");

bool Urma0604UrmaAdviseJettyInvalidParamJettyNullTjettyNullTjetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0604UrmaAdviseJettyInvalidParamJettyNullTjettyNullTjetty::GetName() const
{
    return "urma_advise_jetty 参数非法（jetty == NULL || tjetty == NULL || tjetty->trans_mode != URMA_TM_RM || "
           "jetty->jetty_cfg.jfs_cfg.tran）";
}

std::string Urma0604UrmaAdviseJettyInvalidParamJettyNullTjettyNullTjetty::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || tjetty == NULL || tjetty->trans_mode != URMA_TM_RM || "
           "jetty->jetty_cfg.jfs_cfg.tran`；该路径返回 URMA_EINVAL";
}

RootCause Urma0604UrmaAdviseJettyInvalidParamJettyNullTjettyNullTjetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0604UrmaAdviseJettyInvalidParamJettyNullTjettyNullTjetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0604UrmaAdviseJettyInvalidParamJettyNullTjettyNullTjetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0604UrmaAdviseJettyInvalidParamJettyNullTjettyNullTjetty::GetId() const
{
    return "urma_0604";
}
} // namespace diag
