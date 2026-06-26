#include "urma_failure_660.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure660> g_urma("urma_660");

bool UrmaFailure660::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_discover_devices") != std::string::npos &&
           message.find("open failed, errno:") != std::string::npos;
}

std::string UrmaFailure660::GetName() const
{
    return "设备信息读取或解析失败导致discoverdiscover、devices失败";
}

std::string UrmaFailure660::GetRootCauseDesc() const
{
    return "urma_discover_devices需要从sysfs获取设备信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure660::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure660::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure660::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_discover_devices，open failed, errno:。";
}

std::string UrmaFailure660::GetId() const
{
    return "urma_660";
}
} // namespace diag
