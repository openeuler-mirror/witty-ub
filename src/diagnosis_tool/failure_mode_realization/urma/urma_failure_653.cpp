#include "urma_failure_653.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure653> g_urma("urma_653");

bool UrmaFailure653::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_ioctl_get_eid_list") != std::string::npos &&
           message.find("Failed to open urma cdev with path") != std::string::npos;
}

std::string UrmaFailure653::GetName() const
{
    return "设备EID信息读取或解析失败导致获取ioctl、EID、列表失败";
}

std::string UrmaFailure653::GetRootCauseDesc() const
{
    return "urma_ioctl_get_eid_"
           "list需要从sysfs获取设备EID信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure653::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure653::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure653::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ioctl_get_eid_list，Failed to open urma cdev with path。";
}

std::string UrmaFailure653::GetId() const
{
    return "urma_653";
}
} // namespace diag
