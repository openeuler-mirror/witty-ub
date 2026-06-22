#include "urma_failure_476.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure476> g_urma("urma_476");

bool UrmaFailure476::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jfce") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure476::GetName() const
{
    return "URMA context无效导致创建JFCE失败";
}

std::string UrmaFailure476::GetRootCauseDesc() const
{
    return "urma_create_jfce用于创建JFCE，调用方传入的URMA context不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure476::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure476::GetFixSuggDesc() const
{
    return "当前预期不会出现，如果fd超规格可能导致失败，此时需要修改系统fd规格数，或者减小应用创建jfce的数量";
}

std::string UrmaFailure476::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jfce，Invalid parameter.。";
}

std::string UrmaFailure476::GetId() const
{
    return "urma_476";
}
} // namespace diag
