#include "urma_failure_651.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure651> g_urma("urma_651");

bool UrmaFailure651::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("read_eid_sysfs_with_index") != std::string::npos &&
           message.find("Failed to read sysfs file") != std::string::npos;
}

std::string UrmaFailure651::GetName() const
{
    return "设备EID信息读取或解析失败导致读取EID、sysfs信息、WITH失败";
}

std::string UrmaFailure651::GetRootCauseDesc() const
{
    return "read_eid_sysfs_with_"
           "index需要从sysfs获取设备EID信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure651::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure651::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure651::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：read_eid_sysfs_with_index，Failed to read sysfs file。";
}

std::string UrmaFailure651::GetId() const
{
    return "urma_651";
}
} // namespace diag
