#include "urma_failure_025.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure025> g_urma("urma_025");

bool UrmaFailure025::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_init") != std::string::npos &&
           message.find("Failed to start health check thread.") != std::string::npos;
}

std::string UrmaFailure025::GetName() const
{
    return "sysfs路径信息读取或解析失败导致初始化URMA资源失败";
}

std::string UrmaFailure025::GetRootCauseDesc() const
{
    return "bondp_init需要从sysfs获取sysfs路径信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure025::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure025::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure025::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_init，Failed to start health check thread.。";
}

std::string UrmaFailure025::GetId() const
{
    return "urma_025";
}
} // namespace diag
