#include "urma_failure_341.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure341> g_urma("urma_341");

bool UrmaFailure341::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_unimport_seg") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure341::GetName() const
{
    return "Segment无效导致取消导入Segment失败";
}

std::string UrmaFailure341::GetRootCauseDesc() const
{
    return "urma_unimport_seg用于取消导入Segment，调用方传入的Segment不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure341::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure341::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure341::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unimport_seg，Invalid parameter.。";
}

std::string UrmaFailure341::GetId() const
{
    return "urma_341";
}
} // namespace diag
