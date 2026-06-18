#include "urma_failure_652.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure652> g_urma("urma_652");

bool UrmaFailure652::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("read_eid_sysfs_with_index") != std::string::npos &&
           message.find("Failed to parse eid value, dev name:") != std::string::npos &&
           message.find(", eid idx:") != std::string::npos;
}

std::string UrmaFailure652::GetName() const
{
    return "设备EID信息读取或解析失败导致读取EID、sysfs信息、WITH失败";
}

std::string UrmaFailure652::GetRootCauseDesc() const
{
    return "read_eid_sysfs_with_"
           "index需要从sysfs获取设备EID信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure652::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure652::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure652::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：read_eid_sysfs_with_index，Failed to parse eid value, dev name:，, eid "
           "idx:。";
}

std::string UrmaFailure652::GetId() const
{
    return "urma_652";
}
} // namespace diag
