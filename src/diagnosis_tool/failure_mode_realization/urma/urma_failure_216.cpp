#include "urma_failure_216.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure216> g_urma("urma_216");

bool UrmaFailure216::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_context") != std::string::npos &&
           message.find("Failed to open urma cdev with path") != std::string::npos &&
           message.find(", dev_fd:") != std::string::npos;
}

std::string UrmaFailure216::GetName() const
{
    return "设备EID信息读取或解析失败导致创建context失败";
}

std::string UrmaFailure216::GetRootCauseDesc() const
{
    return "urma_create_"
           "context需要从sysfs获取设备EID信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure216::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure216::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure216::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_context，Failed to open urma cdev with path，, dev_fd:。";
}

std::string UrmaFailure216::GetId() const
{
    return "urma_216";
}
} // namespace diag
