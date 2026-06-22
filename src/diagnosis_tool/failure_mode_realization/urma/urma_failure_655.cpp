#include "urma_failure_655.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure655> g_urma("urma_655");

bool UrmaFailure655::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_query_device_attr") != std::string::npos &&
           message.find("Failed to open urma cdev, path") != std::string::npos;
}

std::string UrmaFailure655::GetName() const
{
    return "设备能力或属性信息读取或解析失败导致查询设备、ATTR失败";
}

std::string UrmaFailure655::GetRootCauseDesc() const
{
    return "urma_query_device_"
           "attr需要从sysfs获取设备能力或属性信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure655::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure655::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure655::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_device_attr，Failed to open urma cdev, path。";
}

std::string UrmaFailure655::GetId() const
{
    return "urma_655";
}
} // namespace diag
