#include "urma_failure_665.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure665> g_urma("urma_665");

bool UrmaFailure665::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_perf_thread_exit_cleanup") != std::string::npos &&
           message.find("Urma perf thread cleanup, thread index") != std::string::npos &&
           message.find("is invalid.") != std::string::npos;
}

std::string UrmaFailure665::GetName() const
{
    return "sysfs路径信息读取或解析失败导致perfPERF、thread、扩展IT失败";
}

std::string UrmaFailure665::GetRootCauseDesc() const
{
    return "urma_perf_thread_exit_"
           "cleanup需要从sysfs获取sysfs路径信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure665::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure665::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure665::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_perf_thread_exit_cleanup，Urma perf thread cleanup, thread "
           "index，is inval"
           "id.。";
}

std::string UrmaFailure665::GetId() const
{
    return "urma_665";
}
} // namespace diag
