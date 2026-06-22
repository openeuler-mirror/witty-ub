#include "urma_failure_686.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure686> g_urma("urma_686");

bool UrmaFailure686::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("wait_async_event_ack") != std::string::npos &&
           message.find("There is an event and it must be acked, acked:") != std::string::npos &&
           message.find(", reported:") != std::string::npos;
}

std::string UrmaFailure686::GetName() const
{
    return "WAIT、event、ACK状态不满足要求导致waitWAIT、event、ACK失败";
}

std::string UrmaFailure686::GetRootCauseDesc() const
{
    return "wait_async_event_ack执行waitWAIT、event、ACK时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure686::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure686::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure686::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：wait_async_event_ack，There is an event and it must be acked, acked:，, "
           "reporte"
           "d:。";
}

std::string UrmaFailure686::GetId() const
{
    return "urma_686";
}
} // namespace diag
