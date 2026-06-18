#include "urma_failure_647.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure647> g_urma("urma_647");

bool UrmaFailure647::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_read_sysfs_file") != std::string::npos &&
           message.find("Failed read file:") != std::string::npos && message.find(", ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure647::GetName() const
{
    return "sysfs路径信息读取或解析失败导致读取sysfs信息、FILE失败";
}

std::string UrmaFailure647::GetRootCauseDesc() const
{
    return "urma_read_sysfs_"
           "file需要从sysfs获取sysfs路径信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure647::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure647::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure647::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_read_sysfs_file，Failed read file:，, ret:，, errno:。";
}

std::string UrmaFailure647::GetId() const
{
    return "urma_647";
}
} // namespace diag
