#include "urma_failure_247.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure247> g_urma("urma_247");

bool UrmaFailure247::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_query_jfr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure247::GetName() const
{
    return "provider未提供modify_jfr操作实现无效导致查询JFR失败";
}

std::string UrmaFailure247::GetRootCauseDesc() const
{
    return "urma_query_jfr用于查询JFR，调用方传入的provider未提供modify_"
           "jfr操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure247::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure247::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure247::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_jfr，Invalid parameter.。";
}

std::string UrmaFailure247::GetId() const
{
    return "urma_247";
}
} // namespace diag
