#include "urma_failure_572.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure572> g_urma("urma_572");

bool UrmaFailure572::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_free_jfr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure572::GetName() const
{
    return "provider未提供query_jfr操作实现无效导致释放JFR失败";
}

std::string UrmaFailure572::GetRootCauseDesc() const
{
    return "urma_free_jfr用于释放JFR，调用方传入的provider未提供query_"
           "jfr操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure572::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure572::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure572::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfr，Invalid parameter.。";
}

std::string UrmaFailure572::GetId() const
{
    return "urma_572";
}
} // namespace diag
