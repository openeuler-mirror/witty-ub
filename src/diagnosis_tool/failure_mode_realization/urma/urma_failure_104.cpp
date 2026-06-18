#include "urma_failure_104.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure104> g_urma("urma_104");

bool UrmaFailure104::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_import_jetty") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure104::GetName() const
{
    return "URMA context、URMA设备、设备sysfs信息、provider操作表无效导致导入Jetty失败";
}

std::string UrmaFailure104::GetRootCauseDesc() const
{
    return "urma_import_jetty用于导入Jetty，调用方传入的URMA "
           "context、URMA设备、设备sysfs信息、provider操作表不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure104::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure104::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure104::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_import_jetty，Invalid parameter.。";
}

std::string UrmaFailure104::GetId() const
{
    return "urma_104";
}
} // namespace diag
