#include "urma_failure_650.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure650> g_urma("urma_650");

bool UrmaFailure650::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("read_eid_sysfs_with_index") != std::string::npos &&
           message.find("snprintf failed, eid idx:") != std::string::npos;
}

std::string UrmaFailure650::GetName() const
{
    return "读取EID、sysfs信息、WITH执行失败导致读取EID、sysfs信息、WITH失败";
}

std::string UrmaFailure650::GetRootCauseDesc() const
{
    return "read_eid_sysfs_with_"
           "index执行读取EID、sysfs信息、WITH时依赖的读取EID、sysfs信息、WITH步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure650::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure650::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure650::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：read_eid_sysfs_with_index，snprintf failed, eid idx:。";
}

std::string UrmaFailure650::GetId() const
{
    return "urma_650";
}
} // namespace diag
