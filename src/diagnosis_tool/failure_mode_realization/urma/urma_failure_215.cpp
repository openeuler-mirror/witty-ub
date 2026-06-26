#include "urma_failure_215.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure215> g_urma("urma_215");

bool UrmaFailure215::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_context") != std::string::npos &&
           message.find("Invalid parameter with err dev or ops.") != std::string::npos;
}

std::string UrmaFailure215::GetName() const
{
    return "URMA设备、provider操作表、create_context无效导致创建context失败";
}

std::string UrmaFailure215::GetRootCauseDesc() const
{
    return "urma_create_context用于创建context，调用方传入的URMA设备、provider操作表、create_"
           "context不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure215::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure215::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure215::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_context，Invalid parameter with err dev or ops.。";
}

std::string UrmaFailure215::GetId() const
{
    return "urma_215";
}
} // namespace diag
