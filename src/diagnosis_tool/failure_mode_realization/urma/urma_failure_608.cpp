#include "urma_failure_608.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure608> g_urma("urma_608");

bool UrmaFailure608::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_start_health_check_thread") != std::string::npos &&
           message.find("Failed to create health check thread") != std::string::npos;
}

std::string UrmaFailure608::GetName() const
{
    return "sysfs路径信息读取或解析失败导致校验start、health、thread失败";
}

std::string UrmaFailure608::GetRootCauseDesc() const
{
    return "bondp_start_health_check_"
           "thread需要从sysfs获取sysfs路径信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure608::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure608::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure608::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_start_health_check_thread，Failed to create health check thread。";
}

std::string UrmaFailure608::GetId() const
{
    return "urma_608";
}
} // namespace diag
