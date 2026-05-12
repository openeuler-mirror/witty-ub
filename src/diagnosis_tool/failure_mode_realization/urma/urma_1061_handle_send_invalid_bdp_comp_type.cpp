#include "urma_1061_handle_send_invalid_bdp_comp_type.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1061HandleSendInvalidBdpCompType> g_urma("urma_1061");

bool Urma1061HandleSendInvalidBdpCompType::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid bdp_comp type: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1061HandleSendInvalidBdpCompType::GetName() const
{
    return "handle_send Invalid bdp_comp type: %";
}

std::string Urma1061HandleSendInvalidBdpCompType::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bjetty_ctx->bdp_comp->comp_type != BONDP_COMP_JETTY && bjetty_ctx->bdp_comp->comp_type "
           "!= BONDP_COMP`；该路径返回 CR_HANDLER_ERR_AND_COPY";
}

RootCause Urma1061HandleSendInvalidBdpCompType::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1061HandleSendInvalidBdpCompType::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1061HandleSendInvalidBdpCompType::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid bdp_comp type: %";
}

std::string Urma1061HandleSendInvalidBdpCompType::GetId() const
{
    return "urma_1061";
}
} // namespace diag
