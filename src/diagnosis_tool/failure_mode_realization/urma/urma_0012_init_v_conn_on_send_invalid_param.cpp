#include "urma_0012_init_v_conn_on_send_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0012InitVConnOnSendInvalidParam> g_urma("urma_0012");

bool Urma0012InitVConnOnSendInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0012InitVConnOnSendInvalidParam::GetName() const
{
    return "init_v_conn_on_send Invalid param";
}

std::string Urma0012InitVConnOnSendInvalidParam::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `v_conn == NULL || target_vjetty == NULL`";
}

RootCause Urma0012InitVConnOnSendInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0012InitVConnOnSendInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0012InitVConnOnSendInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param";
}

std::string Urma0012InitVConnOnSendInvalidParam::GetId() const
{
    return "urma_0012";
}
} // namespace diag
