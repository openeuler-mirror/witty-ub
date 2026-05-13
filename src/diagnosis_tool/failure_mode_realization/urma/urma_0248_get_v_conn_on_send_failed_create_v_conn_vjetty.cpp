#include "urma_0248_get_v_conn_on_send_failed_create_v_conn_vjetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0248GetVConnOnSendFailedCreateVConnVjetty> g_urma("urma_0248");

bool Urma0248GetVConnOnSendFailedCreateVConnVjetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create v_conn for vjetty, ret: %,"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0248GetVConnOnSendFailedCreateVConnVjetty::GetName() const
{
    return "get_v_conn_on_send Failed to create v_conn for vjetty,";
}

std::string Urma0248GetVConnOnSendFailedCreateVConnVjetty::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma0248GetVConnOnSendFailedCreateVConnVjetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0248GetVConnOnSendFailedCreateVConnVjetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0248GetVConnOnSendFailedCreateVConnVjetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create v_conn for vjetty, ret: %,";
}

std::string Urma0248GetVConnOnSendFailedCreateVConnVjetty::GetId() const
{
    return "urma_0248";
}
} // namespace diag
