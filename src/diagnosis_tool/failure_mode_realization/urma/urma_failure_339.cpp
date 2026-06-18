#include "urma_failure_339.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure339> g_urma("urma_339");

bool UrmaFailure339::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_import_seg") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure339::GetName() const
{
    return "URMA context、内存Segment无效导致导入Segment失败";
}

std::string UrmaFailure339::GetRootCauseDesc() const
{
    return "urma_import_seg用于导入Segment，调用方传入的URMA "
           "context、内存Segment不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure339::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure339::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure339::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_import_seg，Invalid parameter.。";
}

std::string UrmaFailure339::GetId() const
{
    return "urma_339";
}
} // namespace diag
