#include "urma_failure_242.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure242> g_urma("urma_242");

bool UrmaFailure242::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_query_jfs") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure242::GetName() const
{
    return "provider未提供modify_jfs操作实现无效导致查询JFS失败";
}

std::string UrmaFailure242::GetRootCauseDesc() const
{
    return "urma_query_jfs用于查询JFS，调用方传入的provider未提供modify_"
           "jfs操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure242::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure242::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure242::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_jfs，Invalid parameter.。";
}

std::string UrmaFailure242::GetId() const
{
    return "urma_242";
}
} // namespace diag
