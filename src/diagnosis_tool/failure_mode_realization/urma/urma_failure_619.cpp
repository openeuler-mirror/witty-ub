#include "urma_failure_619.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure619> g_urma("urma_619");

bool UrmaFailure619::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_query_jfr") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure619::GetName() const
{
    return "ret无效导致查询JFR失败";
}

std::string UrmaFailure619::GetRootCauseDesc() const
{
    return "urma_cmd_query_jfr用于查询JFR，调用方传入的ret不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure619::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure619::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure619::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_query_jfr，Invalid parameter。";
}

std::string UrmaFailure619::GetId() const
{
    return "urma_619";
}
} // namespace diag
