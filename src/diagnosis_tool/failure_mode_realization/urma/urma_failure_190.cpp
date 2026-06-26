#include "urma_failure_190.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure190> g_urma("urma_190");

bool UrmaFailure190::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_jfs") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure190::GetName() const
{
    return "provider未提供flush_jfs操作实现无效导致分配JFS失败";
}

std::string UrmaFailure190::GetRootCauseDesc() const
{
    return "urma_alloc_jfs用于分配JFS，调用方传入的provider未提供flush_"
           "jfs操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure190::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure190::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure190::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jfs，Invalid parameter.。";
}

std::string UrmaFailure190::GetId() const
{
    return "urma_190";
}
} // namespace diag
