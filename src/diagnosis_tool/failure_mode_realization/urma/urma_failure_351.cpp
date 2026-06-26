#include "urma_failure_351.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure351> g_urma("urma_351");

bool UrmaFailure351::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_register_sysfs_dev") != std::string::npos &&
           message.find("Register device failed. Failed to match driver for device") != std::string::npos;
}

std::string UrmaFailure351::GetName() const
{
    return "下层注册或导入返回失败导致注册sysfs信息、设备失败";
}

std::string UrmaFailure351::GetRootCauseDesc() const
{
    return "urma_register_sysfs_"
           "dev在注册sysfs信息、设备时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure351::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure351::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure351::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_register_sysfs_dev，Register device failed. Failed to match driver "
           "for de"
           "vice。";
}

std::string UrmaFailure351::GetId() const
{
    return "urma_351";
}
} // namespace diag
