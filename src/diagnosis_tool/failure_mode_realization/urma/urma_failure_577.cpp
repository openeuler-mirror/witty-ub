#include "urma_failure_577.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure577> g_urma("urma_577");

bool UrmaFailure577::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfr_batch") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure577::GetName() const
{
    return "jfr_arr、bad_jfr无效导致删除JFR失败";
}

std::string UrmaFailure577::GetRootCauseDesc() const
{
    return "urma_delete_jfr_batch用于删除JFR，调用方传入的jfr_arr、bad_jfr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure577::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure577::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure577::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfr_batch，Invalid parameter.。";
}

std::string UrmaFailure577::GetId() const
{
    return "urma_577";
}
} // namespace diag
