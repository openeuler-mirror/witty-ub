#include "urma_failure_436.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure436> g_urma("urma_436");

bool UrmaFailure436::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_set_jfr_opt") != std::string::npos &&
           message.find("jfc not exist in jfr.") != std::string::npos;
}

std::string UrmaFailure436::GetName() const
{
    return "JFR状态不满足要求导致设置JFR失败";
}

std::string UrmaFailure436::GetRootCauseDesc() const
{
    return "urma_cmd_set_jfr_opt执行设置JFR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure436::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure436::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure436::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jfr_opt，jfc not exist in jfr.。";
}

std::string UrmaFailure436::GetId() const
{
    return "urma_436";
}
} // namespace diag
