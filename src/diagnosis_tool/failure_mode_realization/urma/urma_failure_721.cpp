#include "urma_failure_721.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure721> g_urma("urma_721");

bool UrmaFailure721::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jfr_opt") != std::string::npos &&
           message.find("invalid opt id or opt len") != std::string::npos;
}

std::string UrmaFailure721::GetName() const
{
    return "JFR状态不满足要求导致设置JFR失败";
}

std::string UrmaFailure721::GetRootCauseDesc() const
{
    return "urma_set_jfr_opt执行设置JFR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure721::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure721::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure721::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfr_opt，invalid opt id or opt len。";
}

std::string UrmaFailure721::GetId() const
{
    return "urma_721";
}
} // namespace diag
