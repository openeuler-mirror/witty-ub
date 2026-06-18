#include "urma_failure_447.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure447> g_urma("urma_447");

bool UrmaFailure447::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_free_jfc") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure447::GetName() const
{
    return "provider未提供modify_jfc操作实现无效导致释放JFC失败";
}

std::string UrmaFailure447::GetRootCauseDesc() const
{
    return "urma_free_jfc用于释放JFC，调用方传入的provider未提供modify_"
           "jfc操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure447::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure447::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure447::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfc，Invalid parameter.。";
}

std::string UrmaFailure447::GetId() const
{
    return "urma_447";
}
} // namespace diag
