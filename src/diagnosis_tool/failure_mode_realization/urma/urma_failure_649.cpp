#include "urma_failure_649.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure649> g_urma("urma_649");

bool UrmaFailure649::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("read_eid_list_sysyf") != std::string::npos &&
           message.find("Failed to read sysfs file") != std::string::npos;
}

std::string UrmaFailure649::GetName() const
{
    return "设备EID信息读取或解析失败导致读取EID、列表、sysyf失败";
}

std::string UrmaFailure649::GetRootCauseDesc() const
{
    return "read_eid_list_"
           "sysyf需要从sysfs获取设备EID信息，路径不存在、内容读取失败或字段解析异常会导致设备信息不可用。";
}

RootCause UrmaFailure649::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure649::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure649::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：read_eid_list_sysyf，Failed to read sysfs file。";
}

std::string UrmaFailure649::GetId() const
{
    return "urma_649";
}
} // namespace diag
