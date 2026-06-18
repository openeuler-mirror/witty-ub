#include "urma_failure_455.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure455> g_urma("urma_455");

bool UrmaFailure455::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfc_batch") != std::string::npos &&
           message.find("Invalid parameter, index:") != std::string::npos;
}

std::string UrmaFailure455::GetName() const
{
    return "URMA设备、设备sysfs信息、delete_jfc_batch无效导致删除JFC失败";
}

std::string UrmaFailure455::GetRootCauseDesc() const
{
    return "urma_delete_jfc_batch用于删除JFC，调用方传入的URMA设备、设备sysfs信息、delete_jfc_"
           "batch不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure455::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure455::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure455::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfc_batch，Invalid parameter, index:。";
}

std::string UrmaFailure455::GetId() const
{
    return "urma_455";
}
} // namespace diag
