#include "urma_failure_661.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure661> g_urma("urma_661");

bool UrmaFailure661::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_scan_sysfs_devices") != std::string::npos &&
           message.find("open failed, errno:") != std::string::npos;
}

std::string UrmaFailure661::GetName() const
{
    return "设备信息读取或解析失败导致scanSCAN、sysfs信息、devices失败";
}

std::string UrmaFailure661::GetRootCauseDesc() const
{
    return "urma_scan_sysfs_"
           "devices需要从sysfs获取设备信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure661::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure661::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure661::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_scan_sysfs_devices，open failed, errno:。";
}

std::string UrmaFailure661::GetId() const
{
    return "urma_661";
}
} // namespace diag
