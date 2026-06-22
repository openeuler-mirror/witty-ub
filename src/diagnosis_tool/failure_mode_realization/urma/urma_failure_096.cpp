#include "urma_failure_096.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure096> g_urma("urma_096");

bool UrmaFailure096::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_import_jfr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure096::GetName() const
{
    return "URMA context、URMA设备、设备sysfs信息、provider操作表无效导致导入JFR失败";
}

std::string UrmaFailure096::GetRootCauseDesc() const
{
    return "urma_import_jfr用于导入JFR，调用方传入的URMA "
           "context、URMA设备、设备sysfs信息、provider操作表不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure096::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure096::GetFixSuggDesc() const
{
    return "UDMA错误定界；建链交换信息失败，可重试";
}

std::string UrmaFailure096::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_import_jfr，Invalid parameter.。";
}

std::string UrmaFailure096::GetId() const
{
    return "urma_096";
}
} // namespace diag
