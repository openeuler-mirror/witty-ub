#include "urma_1059_handle_recv_failed_create_vconn.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1059HandleRecvFailedCreateVconn> g_urma("urma_1059");

bool Urma1059HandleRecvFailedCreateVconn::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create vconn for ("};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1059HandleRecvFailedCreateVconn::GetName() const
{
    return "handle_recv Failed to create vconn for (";
}

std::string Urma1059HandleRecvFailedCreateVconn::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "CR_HANDLER_ERR_AND_COPY";
}

RootCause Urma1059HandleRecvFailedCreateVconn::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1059HandleRecvFailedCreateVconn::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1059HandleRecvFailedCreateVconn::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create vconn for (";
}

std::string Urma1059HandleRecvFailedCreateVconn::GetId() const
{
    return "urma_1059";
}
} // namespace diag
