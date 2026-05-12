#include "urma_1058_handle_recv_invalid_bdp_comp_type.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1058HandleRecvInvalidBdpCompType> g_urma("urma_1058");

bool Urma1058HandleRecvInvalidBdpCompType::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid bdp_comp type: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1058HandleRecvInvalidBdpCompType::GetName() const
{
    return "handle_recv Invalid bdp_comp type: %";
}

std::string Urma1058HandleRecvInvalidBdpCompType::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bjetty_ctx->bdp_comp->comp_type != BONDP_COMP_JETTY && bjetty_ctx->bdp_comp->comp_type "
           "!= BONDP_COMP`；该路径返回 CR_HANDLER_ERR_AND_COPY";
}

RootCause Urma1058HandleRecvInvalidBdpCompType::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1058HandleRecvInvalidBdpCompType::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1058HandleRecvInvalidBdpCompType::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid bdp_comp type: %";
}

std::string Urma1058HandleRecvInvalidBdpCompType::GetId() const
{
    return "urma_1058";
}
} // namespace diag
