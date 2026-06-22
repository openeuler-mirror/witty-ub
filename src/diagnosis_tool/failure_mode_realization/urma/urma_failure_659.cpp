#include "urma_failure_659.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure659> g_urma("urma_659");

bool UrmaFailure659::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_read_sysfs_device") != std::string::npos &&
           message.find("snprintf failed, dev_name:") != std::string::npos;
}

std::string UrmaFailure659::GetName() const
{
    return "读取sysfs信息、设备执行失败导致读取sysfs信息、设备失败";
}

std::string UrmaFailure659::GetRootCauseDesc() const
{
    return "urma_read_sysfs_"
           "device执行读取sysfs信息、设备时依赖的读取sysfs信息、设备步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure659::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure659::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure659::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_read_sysfs_device，snprintf failed, dev_name:。";
}

std::string UrmaFailure659::GetId() const
{
    return "urma_659";
}
} // namespace diag
