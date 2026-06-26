#include "urma_failure_191.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure191> g_urma("urma_191");

bool UrmaFailure191::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_jfs") != std::string::npos &&
           message.find("Invalid parameter, trans_mode:") != std::string::npos;
}

std::string UrmaFailure191::GetName() const
{
    return "URMA context、配置参数、JFS、JFC无效导致分配JFS失败";
}

std::string UrmaFailure191::GetRootCauseDesc() const
{
    return "urma_alloc_jfs用于分配JFS，调用方传入的URMA "
           "context、配置参数、JFS、JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure191::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure191::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure191::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jfs，Invalid parameter, trans_mode:。";
}

std::string UrmaFailure191::GetId() const
{
    return "urma_191";
}
} // namespace diag
